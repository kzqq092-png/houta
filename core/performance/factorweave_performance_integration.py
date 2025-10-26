from loguru import logger
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FactorWeave-Quant 性能监控集成模块
将现有性能监控系统与DuckDB分析层进行深度融合

功能特性：
1. 统一性能数据收集和存储
2. 实时性能监控与历史分析
3. 多维度性能指标分析
4. 自动化性能报告生成
"""

import time
import threading
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import pandas as pd

from .unified_monitor import (
    UnifiedPerformanceMonitor, PerformanceMetric, PerformanceCategory,
    MetricType, get_performance_monitor
)
from ..database.factorweave_analytics_db import get_analytics_db

logger = logger


@dataclass
class PerformanceBenchmark:
    """性能基准数据类"""
    metric_name: str
    baseline_value: float
    target_value: float
    current_value: float
    improvement_percentage: float
    status: str  # 'excellent', 'good', 'needs_improvement', 'critical'
    threshold: float = 0.0  # 阈值（默认0）
    history: list = None  # 历史数据（默认None）

    def __post_init__(self):
        """初始化后处理"""
        if self.history is None:
            self.history = []


class FactorWeavePerformanceIntegrator:
    """FactorWeave性能监控集成器"""

    def __init__(self):
        self.unified_monitor = get_performance_monitor()
        self.analytics_db = get_analytics_db()
        self.is_running = False
        self.integration_thread = None
        self.sync_interval = 30  # 30秒同步一次

        # 性能基准配置
        self.benchmarks = {
            'query_response_time': {'baseline': 100.0, 'target': 10.0},  # ms
            'strategy_execution_time': {'baseline': 5000.0, 'target': 1000.0},  # ms
            'indicator_calculation_time': {'baseline': 200.0, 'target': 50.0},  # ms
            'pattern_recognition_time': {'baseline': 1000.0, 'target': 200.0},  # ms
            'memory_usage': {'baseline': 500.0, 'target': 300.0},  # MB
            'cpu_usage': {'baseline': 80.0, 'target': 50.0},  # %
        }

        logger.info("FactorWeave性能监控集成器初始化完成")

    def start_integration(self):
        """启动性能监控集成"""
        if self.is_running:
            return

        self.is_running = True
        self.unified_monitor.start()

        # 启动数据同步线程
        self.integration_thread = threading.Thread(
            target=self._integration_loop, daemon=True
        )
        self.integration_thread.start()

    def start_monitoring(self):
        """启动性能监控（别名方法）"""
        return self.start_integration()

        logger.info("FactorWeave性能监控集成已启动")

    def stop_integration(self):
        """停止性能监控集成"""
        self.is_running = False
        if self.integration_thread:
            self.integration_thread.join(timeout=5)

        self.unified_monitor.stop()
        logger.info("FactorWeave性能监控集成已停止")

    def _integration_loop(self):
        """集成主循环"""
        while self.is_running:
            try:
                # 同步性能数据到DuckDB
                self._sync_performance_data()

                # 更新性能基准
                self._update_performance_benchmarks()

                time.sleep(self.sync_interval)

            except Exception as e:
                logger.error(f"性能监控集成循环错误: {e}")
                time.sleep(self.sync_interval)

    def _sync_performance_data(self):
        """同步性能数据到DuckDB分析层"""
        try:
            # 获取最近的性能指标
            recent_metrics = self._get_recent_metrics()

            if not recent_metrics:
                return

            # 批量插入到DuckDB (使用时间戳+随机数生成唯一ID)
            import random
            base_timestamp = int(datetime.now().timestamp() * 1000)  # 毫秒时间戳

            for i, metric in enumerate(recent_metrics):
                # 生成唯一ID：时间戳 + 序号 + 随机数
                unique_id = base_timestamp + i * 1000 + random.randint(1, 999)

                try:
                    with self.analytics_db.pool.get_connection() as conn:
                        # performance_metrics表结构: id, metric_type, metric_name, value, timestamp, tags, created_at
                        # 将所有指标打包到tags JSON中
                        tags_data = {
                            'precision': metric.get('precision', 0.0),
                            'recall': metric.get('recall', 0.0),
                            'f1_score': metric.get('f1_score', 0.0),
                            'accuracy': metric.get('accuracy', 0.0),
                            'execution_time': metric.get('execution_time', 0.0),
                            'memory_usage': metric.get('memory_usage', 0.0),
                            'cpu_usage': metric.get('cpu_usage', 0.0),
                            'signal_quality': metric.get('signal_quality', 0.0),
                            'confidence_avg': metric.get('confidence_avg', 0.0),
                            'patterns_found': metric.get('patterns_found', 0),
                            'robustness_score': metric.get('robustness_score', 0.0),
                            'parameter_sensitivity': metric.get('parameter_sensitivity', 0.0),
                            'conditions': metric.get('conditions', {})
                        }

                        conn.execute("""
                            INSERT INTO performance_metrics 
                            (metric_type, metric_name, value, timestamp, tags)
                            VALUES (?, ?, ?, ?, ?)
                        """, [
                            'pattern_recognition',  # metric_type
                            metric.get('name', 'unknown'),  # metric_name
                            metric.get('overall_score', 0.0),  # value
                            datetime.now(),  # timestamp
                            json.dumps(tags_data)  # tags
                        ])
                        # DuckDB autocommit模式，不需要显式commit
                except Exception as insert_error:
                    logger.debug(f"插入性能指标失败，跳过: {insert_error}")
            logger.debug(f"同步了 {len(recent_metrics)} 条性能数据到DuckDB")

        except Exception as e:
            logger.error(f"同步性能数据失败: {e}")

    def _get_recent_metrics(self) -> List[Dict[str, Any]]:
        """获取最近的性能指标"""
        try:
            # 从统一监控器获取指标
            metrics = []

            # 获取系统性能指标
            try:
                system_stats = self._get_system_stats_safe()
            except Exception as e:
                logger.warning(f"获取系统性能指标失败: {e}")
                system_stats = None

            if system_stats:
                metrics.append({
                    'name': 'system_performance',
                    'execution_time': system_stats.get('response_time', 0),
                    'memory_usage': system_stats.get('memory_percent', 0),
                    'cpu_usage': system_stats.get('cpu_percent', 0),
                    'overall_score': self._calculate_system_score(system_stats),
                    'conditions': {'type': 'system_monitoring'}
                })

            # 获取策略性能指标
            strategy_stats = self._get_strategy_performance_stats()
            if strategy_stats:
                metrics.extend(strategy_stats)

            return metrics

        except Exception as e:
            logger.error(f"获取最近性能指标失败: {e}")
            return []

    def _get_strategy_performance_stats(self) -> List[Dict[str, Any]]:
        """获取策略性能统计"""
        try:
            stats = []

            # 从DuckDB获取最近的策略执行结果
            # 注意：strategy_execution_results表没有confidence列，使用profit_loss作为性能指标
            recent_strategies = self.analytics_db.execute_query("""
                SELECT strategy_name, 
                       AVG(profit_loss) as avg_profit_loss, 
                       COUNT(*) as execution_count,
                       SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate
                FROM strategy_execution_results 
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
                GROUP BY strategy_name
            """)

            for _, row in recent_strategies.iterrows():
                # 使用胜率(win_rate)作为信号质量和可信度的度量
                win_rate = row.get('win_rate', 0.5)
                stats.append({
                    'name': f"strategy_{row['strategy_name']}",
                    'confidence_avg': win_rate,  # 使用胜率代替confidence
                    'patterns_found': row['execution_count'],
                    'signal_quality': win_rate,  # 使用胜率代替confidence
                    'overall_score': self._calculate_strategy_score(row),
                    'conditions': {'type': 'strategy_execution', 'strategy': row['strategy_name']}
                })

            return stats

        except Exception as e:
            logger.error(f"获取策略性能统计失败: {e}")
            return []

    def _calculate_system_score(self, stats: Dict[str, Any]) -> float:
        """计算系统综合评分"""
        try:
            cpu_score = max(0, 1 - stats.get('cpu_percent', 0) / 100)
            memory_score = max(0, 1 - stats.get('memory_percent', 0) / 100)
            response_score = max(0, 1 - min(stats.get('response_time', 0) / 1000, 1))

            return (cpu_score + memory_score + response_score) / 3

        except Exception:
            return 0.5

    def _calculate_strategy_score(self, row: pd.Series) -> float:
        """计算策略综合评分"""
        try:
            # 使用胜率作为策略质量得分
            win_rate_score = row.get('win_rate', 0.5)
            activity_score = min(row.get('execution_count', 0) / 10, 1.0)

            # 如果有盈亏数据，也纳入评分
            avg_profit = row.get('avg_profit_loss', 0)
            profit_score = 0.5  # 默认值
            if avg_profit > 0:
                profit_score = min(0.5 + (avg_profit / 100), 1.0)  # 归一化盈利
            elif avg_profit < 0:
                profit_score = max(0.5 + (avg_profit / 100), 0.0)  # 归一化亏损

            # 综合评分：胜率40% + 活跃度30% + 盈利30%
            return (win_rate_score * 0.4 + activity_score * 0.3 + profit_score * 0.3)

        except Exception:
            return 0.5

    def _update_performance_benchmarks(self):
        """更新性能基准"""
        try:
            benchmarks = []

            for metric_name, config in self.benchmarks.items():
                current_value = self._get_current_metric_value(metric_name)
                if current_value is not None:
                    benchmark = PerformanceBenchmark(
                        metric_name=metric_name,
                        baseline_value=config['baseline'],
                        target_value=config['target'],
                        current_value=current_value,
                        improvement_percentage=self._calculate_improvement(
                            config['baseline'], config['target'], current_value
                        ),
                        status=self._get_benchmark_status(
                            config['baseline'], config['target'], current_value
                        )
                    )
                    benchmarks.append(benchmark)

            # 存储基准数据
            self._store_benchmarks(benchmarks)

        except Exception as e:
            logger.error(f"更新性能基准失败: {e}")

    def _get_current_metric_value(self, metric_name: str) -> Optional[float]:
        """获取当前指标值"""
        try:
            if metric_name == 'query_response_time':
                # performance_metrics表使用timestamp列，不是test_time
                result = self.analytics_db.execute_query("""
                    SELECT AVG(value) as avg_time
                    FROM performance_metrics 
                    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 5 MINUTE
                      AND metric_name = 'execution_time'
                      AND value > 0
                """)
                return result.iloc[0]['avg_time'] if not result.empty else None

            elif metric_name in ['memory_usage', 'cpu_usage']:
                try:
                    stats = self._get_system_stats_safe()
                    return stats.get(metric_name.replace('_usage', '_percent'), None) if stats else None
                except Exception:
                    return None

            # 其他指标的获取逻辑...

        except Exception as e:
            logger.error(f"获取指标值失败 {metric_name}: {e}")
            return None

    def _calculate_improvement(self, baseline: float, target: float, current: float) -> float:
        """计算改进百分比"""
        if baseline == target:
            return 0.0

        if target < baseline:  # 越小越好的指标
            if current <= target:
                return 100.0
            elif current >= baseline:
                return 0.0
            else:
                return ((baseline - current) / (baseline - target)) * 100
        else:  # 越大越好的指标
            if current >= target:
                return 100.0
            elif current <= baseline:
                return 0.0
            else:
                return ((current - baseline) / (target - baseline)) * 100

    def _get_benchmark_status(self, baseline: float, target: float, current: float) -> str:
        """获取基准状态"""
        improvement = self._calculate_improvement(baseline, target, current)

        if improvement >= 90:
            return 'excellent'
        elif improvement >= 70:
            return 'good'
        elif improvement >= 30:
            return 'needs_improvement'
        else:
            return 'critical'

    def _store_benchmarks(self, benchmarks: List[PerformanceBenchmark]):
        """存储性能基准"""
        try:
            import random
            base_timestamp = int(datetime.now().timestamp() * 1000)  # 毫秒时间戳

            for i, benchmark in enumerate(benchmarks):
                # 生成唯一ID：时间戳 + 序号 + 随机数 + 偏移量
                unique_id = base_timestamp + i * 1000 + random.randint(1, 999) + 50000

                try:
                    with self.analytics_db.pool.get_connection() as conn:
                        # 使用optimization_logs表存储性能基准
                        benchmark_data = {
                            'metric_name': benchmark.metric_name,
                            'threshold': benchmark.threshold,
                            'current_value': benchmark.current_value,
                            'status': benchmark.status,
                            'history': benchmark.history
                        }

                        conn.execute("""
                            INSERT INTO optimization_logs 
                            (optimization_type, parameters, result, improvement, timestamp, metadata)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, [
                            'performance_benchmark',
                            json.dumps({'metric_name': benchmark.metric_name}),
                            benchmark.current_value,
                            0.0,  # improvement placeholder
                            datetime.now(),
                            json.dumps(benchmark_data)
                        ])
                        # DuckDB autocommit模式，不需要显式commit
                except Exception as insert_error:
                    logger.debug(f"插入性能基准失败，跳过: {insert_error}")

        except Exception as e:
            logger.error(f"存储性能基准失败: {e}")

    @contextmanager
    def measure_operation(self, operation_name: str, category: str = 'custom'):
        """测量操作性能的上下文管理器"""
        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()

            execution_time = (end_time - start_time) * 1000  # 转换为毫秒
            memory_delta = end_memory - start_memory if start_memory and end_memory else 0

            # 记录到统一监控器
            self.unified_monitor.record_metric(
                f"{operation_name}_execution_time",
                execution_time,
                PerformanceCategory.ALGORITHM,
                MetricType.HISTOGRAM
            )

            if memory_delta != 0:
                self.unified_monitor.record_metric(
                    f"{operation_name}_memory_delta",
                    memory_delta,
                    PerformanceCategory.SYSTEM,
                    MetricType.GAUGE
                )

    def _get_system_stats_safe(self) -> Optional[Dict[str, Any]]:
        """安全获取系统统计信息"""
        try:
            # 尝试使用psutil直接获取系统信息
            import psutil
            import os

            # 获取磁盘使用率，Windows和Linux路径不同
            disk_path = 'C:\\' if os.name == 'nt' else '/'
            disk_usage = psutil.disk_usage(disk_path)

            return {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': (disk_usage.used / disk_usage.total) * 100,
                'response_time': 1.0  # 默认响应时间
            }
        except ImportError as e:
            # psutil不可用时记录错误并返回None
            logger.error(f"psutil模块不可用，无法获取系统统计信息: {e}")
            logger.error("请安装psutil模块: pip install psutil")
            return None
        except Exception as e:
            logger.error(f"获取系统统计信息失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return None

    def _get_memory_usage(self) -> Optional[float]:
        """获取当前内存使用量"""
        try:
            stats = self._get_system_stats_safe()
            return stats.get('memory_percent', None) if stats else None
        except Exception:
            return None

    def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """获取性能仪表板数据"""
        try:
            # 获取性能基准
            benchmarks_data = self.analytics_db.execute_query("""
                SELECT data FROM analysis_cache 
                WHERE cache_type = 'performance_benchmark'
                  AND expires_at > CURRENT_TIMESTAMP
                ORDER BY created_at DESC
            """)

            benchmarks = []
            for _, row in benchmarks_data.iterrows():
                try:
                    benchmark_dict = json.loads(row['data'])
                    benchmarks.append(benchmark_dict)
                except json.JSONDecodeError:
                    continue

            # 获取系统当前状态
            try:
                current_stats = self._get_system_stats_safe()
            except Exception as e:
                logger.warning(f"获取系统状态失败: {e}")
                current_stats = None

            return {
                'benchmarks': benchmarks,
                'current_stats': current_stats,
                'last_updated': datetime.now().isoformat(),
                'system_status': 'healthy'  # 简化状态判断，移除智能洞察依赖
            }

        except Exception as e:
            logger.error(f"获取性能仪表板数据失败: {e}")
            return {
                'benchmarks': [],
                'current_stats': {},
                'last_updated': datetime.now().isoformat(),
                'error': str(e)
            }

    # 集成测试兼容方法
    def collect_performance_metrics(self) -> List[Dict[str, Any]]:
        """收集性能指标 - 集成测试兼容方法"""
        return self._get_recent_metrics()

    def sync_performance_data(self) -> bool:
        """同步性能数据 - 集成测试兼容方法"""
        try:
            self._sync_performance_data()
            return True
        except Exception as e:
            logger.error(f"同步性能数据失败: {e}")
            return False

    def get_real_time_metrics(self) -> Optional[Dict[str, Any]]:
        """获取实时指标 - 集成测试兼容方法"""
        try:
            system_stats = self._get_system_stats_safe()
            recent_metrics = self._get_recent_metrics()

            return {
                'system_stats': system_stats,
                'recent_metrics': recent_metrics,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取实时指标失败: {e}")
            return None

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """检测异常 - 基于系统指标的简单异常检测"""
        try:
            anomalies = []

            # 基于系统指标进行简单异常检测
            try:
                current_stats = self._get_system_stats_safe()
                if current_stats:
                    # CPU使用率异常
                    if current_stats.get('cpu_percent', 0) > 90:
                        anomalies.append({
                            'type': 'system_anomaly',
                            'metric': 'cpu_usage',
                            'severity': 'high',
                            'description': f"CPU使用率过高: {current_stats['cpu_percent']:.1f}%",
                            'timestamp': datetime.now().isoformat()
                        })

                    # 内存使用率异常
                    if current_stats.get('memory_percent', 0) > 90:
                        anomalies.append({
                            'type': 'system_anomaly',
                            'metric': 'memory_usage',
                            'severity': 'high',
                            'description': f"内存使用率过高: {current_stats['memory_percent']:.1f}%",
                            'timestamp': datetime.now().isoformat()
                        })

                    # 磁盘使用率异常
                    if current_stats.get('disk_percent', 0) > 95:
                        anomalies.append({
                            'type': 'system_anomaly',
                            'metric': 'disk_usage',
                            'severity': 'medium',
                            'description': f"磁盘使用率过高: {current_stats['disk_percent']:.1f}%",
                            'timestamp': datetime.now().isoformat()
                        })
            except Exception as e:
                logger.warning(f"系统指标异常检测失败: {e}")

            return anomalies

        except Exception as e:
            logger.error(f"检测异常失败: {e}")
            return []


# 全局实例和工厂函数
_performance_integrator = None


def get_performance_integrator() -> FactorWeavePerformanceIntegrator:
    """获取性能监控集成器的全局实例"""
    global _performance_integrator
    if _performance_integrator is None:
        _performance_integrator = FactorWeavePerformanceIntegrator()
    return _performance_integrator

# 便捷装饰器


def measure_factorweave_performance(operation_name: str, category: str = 'custom'):
    """FactorWeave性能测量装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            integrator = get_performance_integrator()
            with integrator.measure_operation(operation_name, category):
                return func(*args, **kwargs)
        return wrapper
    return decorator
